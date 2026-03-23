import asyncio
import uvicorn
import argparse

def main():
    parser = argparse.ArgumentParser(description="Emotional Companion Runner")
    parser.add_argument("--mode", choices=["cli", "api"], default="api", help="Run mode: 'api' for web interface, 'cli' for terminal")
    args = parser.parse_args()
    
    if args.mode == "cli":
        from src.interfaces.cli import chat_loop
        asyncio.run(chat_loop())
    else:
        print("启动 Web API 服务器...")
        print("请在浏览器中访问: http://127.0.0.1:8002")
        uvicorn.run("src.interfaces.api:app", host="127.0.0.1", port=8002, reload=True)

if __name__ == "__main__":
    main()