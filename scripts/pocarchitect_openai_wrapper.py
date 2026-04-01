import argparse
import os
from openai import OpenAI
from datetime import datetime

def main():
    parser = argparse.ArgumentParser(description="POCArchitect OpenAI Wrapper")
    parser.add_argument("--url", required=True, help="Single URL or path to batch_urls.txt")
    parser.add_argument("--api-key", required=True, help="OpenAI API key")
    parser.add_argument("--model", default="gpt-5-turbo", help="Model name")
    args = parser.parse_args()

    client = OpenAI(api_key=args.api_key)

    with open("POCArchitect_Prompt-FINAL.md", "r", encoding="utf-8") as f:
        system_prompt = f.read()

    if os.path.isfile(args.url) and args.url.endswith(".txt"):
        with open(args.url, "r", encoding="utf-8") as f:
            user_input = f.read()
    else:
        user_input = args.url

    response = client.chat.completions.create(
        model=args.model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ],
        temperature=0.0
    )

    output = response.choices[0].message.content
    timestamp = datetime.now().strftime("%Y-%m-%d")
    filename = f"POCArchitect_Reports_{timestamp}/report.md" if "batch" in args.url.lower() else f"POCArchitect_Report_{timestamp}.md"
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    with open(filename, "w", encoding="utf-8") as f:
        f.write(output)

    print(f"✅ Report saved: {filename}")

if __name__ == "__main__":
    main()