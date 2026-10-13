FROM node:24.15.0-alpine
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
USER node
EXPOSE 3100
CMD ["npm", "run", "start", "--", "--hostname", "0.0.0.0"]
