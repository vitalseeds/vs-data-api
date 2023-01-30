
# Run directly from Task scheduler 
# (export:task_scheduler_startup_api.xml)
# Start-Sleep -Seconds 1.5
cd $env:VSDATA_API_ROOT
dotenv run -- uvicorn main:app --reload