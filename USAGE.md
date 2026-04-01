Usage Instructions
Single URL Mode
User message:
texthttps://github.com/offsec-tools/some-poc
Batch Mode

Create batch_urls.txt with one URL per line
Upload the file OR paste its content
POCArchitect will generate POCArchitect_Reports_YYYY-MM-DD/ with every report + index.md


Automation Scripts (Optional)
See scripts/ folder for ready-to-run Python wrappers.

pip install openai requests tqdm
python scripts/pocarchitect_xai_wrapper.py --url https://github.com/... --api-key xai-...