from core.user import User
from core.task import Task
from services.corpus_service import CorpusService
from services.ml_service import MLService
from services.analytics_service import AnalyticsService

# init
corpus_service = CorpusService()
ml_service = MLService()
analytics = AnalyticsService(corpus_service, ml_service)

# user
user = User("alice", "alice@mail.com")

# corpus
corpus_id = "corpus_1"
corpus_service.add_corpus(corpus_id, "this is a test this is a test this is")

# task
task = Task(user.id, corpus_id, "zipf")

# run
analytics.execute_task(task)

print(task.get_result())
