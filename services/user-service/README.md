# Task Management Microservices Platform | User Service

---

## User Service (FastAPI): User CRUD 

## Installation
### Windows
1. Install the required packages from requirements.txt
    ```shell
    pip install -r requirements.txt
    ```

2. Run the main.py file:
  ```shell
  python app/main.py
  ```
  
  OR
  
  ```shell
  uvicorn app.main:app --reload --port 8001
  ```

### Docker
To run this project in a Docker image, open your terminal in the same directory as the listed Dockerfile:
1. Build the Docker image:
   ```sh
   docker build -t user-service:latest .   
   ```
2. Run the Docker image for PostgreSQL:
   ```sh
   docker run -d --name postgres-test -e POSTGRES_DB=user_service -e POSTGRES_USER=your_username -e POSTGRES_PASSWORD=your_password -p 5432:5432 postgres:17-alpine
   ```
3. Run the task-service Docker image:
   ```sh
   docker run -p 8001:8001 user-service:latest
   ```
4. Click on the following link to access the web application: http://localhost:8001/docs/
