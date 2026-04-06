from core.task import TaskStatus


class AnalyticsService:
    def __init__(self, corpus_service, ml_service):
        self._corpus_service = corpus_service
        self._ml_service = ml_service

    def execute_task(self, task):
        task.set_status(TaskStatus.RUNNING)

        try:
            tokens = self._corpus_service.get_tokens(task._Task__corpus_id)
            result = self._ml_service.run_model(task._Task__model_name, tokens)

            task.set_result(result)
            task.set_status(TaskStatus.DONE)

        except Exception:
            task.set_status(TaskStatus.FAILED)