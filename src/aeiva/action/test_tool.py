from aeiva.action.tool.tool import Tool
import asyncio

async def test_async_tool():
    # Test async function
    tool = Tool(api_name="async_test_operation")
    result = await tool.execute({'a': 7, 'b': 8})
    print(result)

async def test_sync_tool():
    # Test synchronous function
    tool = Tool(api_name="test_operation")
    result = await tool.execute({'a': 7, 'b': 8})
    print(result)

async def test_rapid_api():
    # test Wrapped RapidAPI function
    tool = Tool(api_name="fun_facts")
    result = await tool.execute({}) # here you can also provide rapidapi_key parameter, as it is optional, either input as param or read from .env
    print(result)


if __name__ == "__main__":    
    # Test sync tool
    asyncio.run(test_sync_tool())

    # Test async tool
    asyncio.run(test_async_tool())

    # # Test Rapid API
    # asyncio.run(test_rapid_api())