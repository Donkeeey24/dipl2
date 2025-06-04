FROM node:20-alpine

WORKDIR /app

COPY package.json ./
# Pokud máš package-lock.json, odkomentuj další řádek:
# COPY package-lock.json ./

RUN npm install

COPY . .

EXPOSE 3000

CMD ["npm", "start"]