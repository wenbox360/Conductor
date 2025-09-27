# prompts.py

from fastmcp import FastMCP, Context

def register_prompts(mcp: FastMCP):
    """Register all prompt templates with the MCP server."""
    
    @mcp.prompt
    async def example_prompt(context: Context, topic: str) -> str:
        """Example prompt template - replace with your actual prompts."""
        return f"Please provide information about {topic}."
    
    @mcp.prompt
    async def code_review_prompt(context: Context, code: str, language: str = "python") -> str:
        """Code review prompt template."""
        return f"Please review this {language} code:\n\n{code}"