FROM ubuntu:noble-20250127

RUN apt update && apt install -y nodejs npm

WORKDIR /app
COPY . /app

RUN npm install

CMD ["npm", "run", "dev"]
