#!/usr/bin/env python3
"""Simple MCP Client for calculator server and Ollama"""

import asyncio
import json
import sys
from typing import Dict, Any
import httpx

class MCPCalculatorClient:
    def __init__(self, ollama_model: str = "qwen3:1.7b"):
        self.ollama_model = ollama_model
        self.server_process = None
        self.tools = {}
        
    async def start_mcp_server(self):
        """Start MCP calculator server subprocess"""
        self.server_process = await asyncio.create_subprocess_exec(
            sys.executable, "server.py",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await self._initialize_connection()
    
    async def _initialize_connection(self):
        """Initialize connection and get tools"""
        # Initialize connection
        init_request = {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "calculator-client", "version": "1.0.0"}
            }
        }
        await self._send_request(init_request)
        
        # Get available tools
        tools_request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        response = await self._send_request(tools_request)
        
        if response and "result" in response:
            for tool in response["result"].get("tools", []):
                self.tools[tool["name"]] = tool
    
    async def _send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send request to MCP server"""
        if not self.server_process:
            return {}
            
        try:
            request_json = json.dumps(request) + "\n"
            self.server_process.stdin.write(request_json.encode())
            await self.server_process.stdin.drain()
            response_line = await asyncio.wait_for(self.server_process.stdout.readline(), timeout=5.0)
            return json.loads(response_line.decode().strip()) if response_line else {}
        except asyncio.TimeoutError:
            print("Timeout waiting for server response")
            return {}
        except Exception as e:
            print(f"Error communicating with server: {e}")
            return {}
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call tool on MCP server"""
        request = {
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments}
        }
        
        response = await self._send_request(request)
        return response["result"]["content"][0]["text"] if response and "result" in response else "Error calling tool"
    
    async def chat_with_ollama(self, message: str) -> str:
        """Send message to Ollama and get response"""
        tools_desc = "\n".join([f"- {name}: {tool.get('description', 'No description')}" 
                          for name, tool in self.tools.items()])
        
        system_prompt = f"""You are a helpful assistant with calculator tools.

Available tools:
{tools_desc}

For calculations, use this format: {{"tool": "tool_name", "arguments": {{"param1": value1, "param2": value2}}}}

For regular conversation, just respond normally."""

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://20.124.80.150:11434/api/generate",
                    json={
                        "model": self.ollama_model,
                        "prompt": f"System: {system_prompt}\n\nUser: {message}\n\nAssistant:",
                        "stream": False,
                        "think": False
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return response.json().get("response", "No response from Ollama")
                return f"Error from Ollama: {response.status_code}"
        except Exception as e:
            return f"Error connecting to Ollama: {e}"
    
    async def process_response(self, response: str) -> str:
        """Process response and execute tools if needed"""
        try:
            # Look for JSON in the response
            if response.strip().startswith("{") and response.strip().endswith("}"):
                return response
        except Exception as e:
            return f"Error processing tool call: {e}"
        
        return response
    
    async def chat_loop(self):
        """Main chat loop"""
        print("Calculator Chat Bot (powered by Ollama + MCP)")
        print("Type 'quit' to exit")
        print("=" * 50)
        
        while True:
            try:
                user_input = input("\nYou: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    break
                if not user_input:
                    continue
                
                response = await self.chat_with_ollama(user_input)
                final_response = await self.process_response(response)
                print(f"Bot: {final_response}")
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
    
    async def cleanup(self):
        """Clean up resources"""
        if self.server_process:
            self.server_process.terminate()
            await self.server_process.wait()

async def main():
    client = MCPCalculatorClient()
    
    try:
        print("Starting MCP Calculator Server...")
        await client.start_mcp_server()
        
        if client.server_process.returncode is not None:
            stderr = await client.server_process.stderr.read()
            print(f"Server exited with code {client.server_process.returncode}: {stderr.decode()}")
            return
        
        print("Connected to MCP server!")
        print("Testing connection to Ollama...")
        
        test_response = await client.chat_with_ollama("Hello")
        if "Error" in test_response:
            print(f"Ollama connection failed: {test_response}")
            print("Make sure Ollama is running: ollama serve")
            return
        
        print("Connected to Ollama!")
        await client.chat_loop()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())