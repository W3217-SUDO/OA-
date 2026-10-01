FROM node:22-alpine AS build
ARG SOURCE_COMMIT
ENV SOURCE_COMMIT=$SOURCE_COMMIT
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY src ./src
COPY public ./public
COPY scripts/build-production.mjs ./scripts/build-production.mjs
COPY index.html tsconfig.json tsconfig.node.json vite.config.ts ./
RUN npm run build

FROM nginx:1.29-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
