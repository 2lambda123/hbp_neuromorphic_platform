Version 3 of the HBP/EBRAINS Neuromorphic Computing Job Queue API, incorporating the Quotas API.

For local development, run:

  uvicorn simqueue.main:app --reload

To run tests:

  pytest --cov=simqueue --cov-report=term --cov-report=html