# Moved into the Control Center

Listing drafts now run inside the local EarnItNotGiven Control Center.

```
cd tools\control-center
copy .env.example .env
start.bat
```

Open http://127.0.0.1:8765 and use Listings. Ollama stays on this PC. Nothing is published until you click Approve.

`lister.py` is still here if you want the old command-line path. It only writes review files and still refuses any Ollama address that is not this computer.
