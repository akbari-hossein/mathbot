<p align="center">
  <img src="mathbot.png" alt="mathbot banner" />
</p>

# mathbot

MathBot is an innovative, full-stack programming competition platform built to serve both traditional ICPC-style contests and modern online challenges. By leveraging DOMjudge for automated judging, Django for backend management, ReactJS for the frontend, and Solidity-based smart contracts for secure, decentralized payments, MathBot creates a reliable and futuristic environment for coders to compete.

## API endpoint

```
List of available API (browseable) at /api
* /accounts/register/
* /accounts/{username}/edit
* /posts/
* /posts/create/
* /posts/{id}/
* /posts/{id}/delete/
* /comments/
* /comments/create/
* /comments/{id}/
* /comments/{id}/delete/
* /token/
* /token/refresh/
```

## Installation with Docker

1. Clone the Repository

```
git clone https://github.com/akbari-hossein/mathbot
cd mathbot
```

2. Set Up Environment Variables

Before running the containers, you need to create .env files for both the backend and frontend.

- Navigate to the backend/ folder:

```
cd backend
cp .env.example .env
```

- Navigate to the frontend/ folder:

```
cd ../frontend
cp .env.example .env
```

Make sure to update the .env files with the correct values if needed.

3. Build and Start the Project
   
From the project root directory, run:

```
docker-compose up --build
```

4. Access the Application

After the containers are up and running:

Frontend: http://localhost:3000

Backend API: http://localhost:8000

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](./CONTRIBUTING.md) file for more info

## Social Networks

[<img src="https://www.vectorlogo.zone/logos/instagram/instagram-tile.svg" width="32">](https://www.instagram.com/themathbot)
[<img src="https://www.vectorlogo.zone/logos/telegram/telegram-tile.svg" width="32">](http://t.me/math_20_bot)
