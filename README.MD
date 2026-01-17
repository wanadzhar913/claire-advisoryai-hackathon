### Getting started:
You'll first have to clone the project and then your can start it using `docker compose`.
```bash
git clone https://github.com/irfannaqieb/claire.git
cd claire

docker compose --env-file .env  up --build
docker compose down -v
```

You'll be able to access the following services locally:
- Backend API: http://localhost:8000/docs
- MinIO Portal: http://localhost:9000 (username: admin, password: admin123)