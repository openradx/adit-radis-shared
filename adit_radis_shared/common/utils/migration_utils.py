from string import Template


def procrastinate_on_delete_sql(app_name: str, model_name: str, reverse=False):
    """Create the SQL to set the on_delete behavior of a foreign key to SET_NULL.

    As Procrastinate uses custom SQL to delete jobs and we use a OneToOneField to link
    to the job, we need to set the on_delete behavior at the database level as the
    Django's on_delete method won't be respected (which is at the application level
    only and not at the database level).
    Also see https://code.djangoproject.com/ticket/21961
    """
    template = """
        ALTER TABLE ${app_name}_${model_name}
        DROP CONSTRAINT ${app_name}_${model_name}_queued_job_id_key,
        ADD CONSTRAINT ${app_name}_${model_name}_queued_job_id_key
        FOREIGN KEY (queued_job_id) 
        REFERENCES procrastinate_jobs(id) 
        """

    if not reverse:
        template += "\nON DELETE SET NULL;"

    return Template(template).substitute(app_name=app_name, model_name=model_name)
