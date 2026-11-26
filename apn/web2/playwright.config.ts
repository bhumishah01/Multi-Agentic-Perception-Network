import{defineConfig}from'@playwright/test';
export default defineConfig({testDir:'tests',use:{baseURL:'http://127.0.0.1:8766',channel:'chrome'},webServer:{command:'.venv/bin/python -m uvicorn apn.api.main:app --host 127.0.0.1 --port 8766',cwd:'..',url:'http://127.0.0.1:8766/api/health',reuseExistingServer:true}});
