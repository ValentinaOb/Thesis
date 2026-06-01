FROM node:20-alpine

WORKDIR /app

COPY package.json .
RUN npm install --production

COPY app ./app

RUN mkdir -p /app/app/uploads

EXPOSE 3000
CMD ["npm", "start"]
