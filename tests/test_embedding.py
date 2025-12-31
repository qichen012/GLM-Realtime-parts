import asyncio
from openai import AsyncOpenAI

async def test():
    client = AsyncOpenAI(
        base_url="https://api.zhizengzeng.com/v1",
        api_key="sk-zk2612b8762a500bfc599c85336efbe645568d3afac6a652"
    )
    
    try:
        response = await client.embeddings.create(
            model="qwen3-embedding-8b",
            input=["Hello, world!"],
            encoding_format="float"
        )
        print(f"Success! Response: {response}")
        print(f"Data: {response.data}")
        print(f"First embedding length: {len(response.data[0].embedding)}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(test())