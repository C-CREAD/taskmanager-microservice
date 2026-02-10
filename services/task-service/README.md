# Task Management Microservices Platform | Task Service

---

## Task Service (Django REST): Task CRUD & management


## Installation
### Windows
1. Install the required packages from requirements.txt
    ```shell
    pip install -r requirements.txt
    ```

2. Make and apply all migrations to the manage.py file:
    ```shell
    python manage.py makemigrations
    python manage.py migrate
    ```
    
3. Run the manage.py file:
    ```shell
    python manage.py runserver
    ```

### Docker
To run this project in a Docker image, open your terminal in the same directory as the listed Dockerfile:
1. Build the Docker image:
   ```sh
   docker build -t task-service:latest .   
   ```
2. Run the Docker image for PostgreSQL:
   ```sh
   docker run -d --name postgres-test -e POSTGRES_DB=task_management -e POSTGRES_USER=your_username -e POSTGRES_PASSWORD=your_password -p 5432:5432 postgres:17-alpine
   ```
3. Run the task-service Docker image:
   ```sh
   docker run -d --name postgres-test -e POSTGRES_DB=task_management -e POSTGRES_USER=your_username -e POSTGRES_PASSWORD=your_password -p 5432:5432 postgres:17-alpine
   ```
4. Click on the following link to access the web application: http://localhost:8000/api/
