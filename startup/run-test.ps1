
# Run directly from Task scheduler 
# (export:task_scheduler_startup_api.xml)
# Start-Sleep -Seconds 1.5
cd $env:VSDATA_API_ROOT
dotenv -f .env-test run -- uvicorn main:app --reload --host 0.0.0.0