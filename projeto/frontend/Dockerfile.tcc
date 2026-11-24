FROM node:22-bookworm-slim
WORKDIR /app
COPY package*.json ./
ENV PUPPETEER_SKIP_DOWNLOAD=true
RUN npm ci --legacy-peer-deps --no-audit --no-fund
COPY . .
RUN cp config/prod.env.js.EXAMPLE config/prod.env.js
CMD ["./node_modules/.bin/webpack-dev-server", "--config", "build/webpack.dev.conf.js"]
