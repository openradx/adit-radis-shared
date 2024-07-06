import procrastinate
from procrastinate.contrib.django import app


@app.task(pass_context=True)
def example_task(context: procrastinate.JobContext):
    job = context.job
    assert job
    job_id = job.id
    assert job_id is not None
    print(f"Hello from job {job_id}")


# Every night at 3am
@app.periodic(cron="0 3 * * *")
@app.task
def periodic_example_task(timestamp: int):
    print(f"A periodic hello at {timestamp}!")
