"""Test connection to z.ai provider

This script tests your z.ai API credentials.
"""
import os
import sys
import asyncio

from opencode_python.llm import LLMClient


async def main():
    """Test z.ai connection"""

    provider_id = os.getenv("LLM_PROVIDER", "zai-coding-plan")
    api_key = os.getenv(f"{provider_id.upper().replace('-', '_')}_API_KEY")
    base_url = os.getenv("LLM_BASE_URL")
    model = os.getenv("LLM_MODEL", "glm-4.7")

    print(f"Testing connection to {provider_id}")
    print(f"Model: {model}")
    print(f"Base URL: {base_url or 'default'}")
    print()

    if not api_key:
        print(f"Error: {provider_id.upper().replace('.', '_')}_API_KEY not set")
        print(f"Set it with: export {provider_id.upper().replace('.', '_')}_API_KEY='your-api-key'")
        sys.exit(1)

    client = LLMClient(
        provider_id=provider_id,
        api_key=api_key,
        base_url=base_url,
        model=model,
    )

    print("Testing connection...")
    print("-" * 50)

    try:
        result = await client.test_connection()

        print(f"Status: {result['status']}")
        print(f"Provider: {result['provider']}")
        print(f"Model: {result['model_name']}")
        print(f"Base URL: {result['base_url']}")
        print()

        if result["connected"]:
            print(f"Response: {result['response']}")
            print("-" * 50)
            print("SUCCESS: Connection is working!")
            print()
            print("You can now run PR review with:")
            print("  python examples/pr_review_example.py")
            return 0
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
            print()
            print("Troubleshooting:")
            print("  - Check API key is correct")
            print("  - Try setting LLM_BASE_URL if using custom endpoint")
            print("  - Check base URL matches your z.ai API documentation")
            return 1

    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        print()
        print("Full error details for debugging:")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
