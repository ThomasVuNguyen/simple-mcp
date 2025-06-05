#!/usr/bin/env python3
"""
Simple MCP Calculator Server using fastmcp
"""

import asyncio
from fastmcp import FastMCP

# Create the MCP server
mcp = FastMCP("Calculator Server")

@mcp.tool()
def add(a: float, b: float) -> float:
    """Add two numbers together"""
    return a + b

@mcp.tool()
def subtract(a: float, b: float) -> float:
    """Subtract b from a"""
    return a - b

@mcp.tool()
def multiply(a: float, b: float) -> float:
    """Multiply two numbers"""
    return a * b

@mcp.tool()
def divide(a: float, b: float) -> float:
    """Divide a by b"""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

@mcp.tool()
def power(a: float, b: float) -> float:
    """Raise a to the power of b"""
    return a ** b

@mcp.tool()
def square_root(a: float) -> float:
    """Calculate the square root of a number"""
    if a < 0:
        raise ValueError("Cannot calculate square root of negative number")
    return a ** 0.5

def main():
    """Run the MCP server"""
    # Don't use asyncio.run() since fastmcp's run() already handles the event loop
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()