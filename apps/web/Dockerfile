FROM oven/bun:1.3.5-alpine AS builder

WORKDIR /app

ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

COPY package.json bun.lock ./
RUN bun install --frozen-lockfile

COPY . .
RUN bun run build


FROM node:20-alpine

WORKDIR /app

# Install a pinned static server for production asset delivery.
RUN npm install -g serve@14.2.4

# Built assets from builder stage
COPY --from=builder /app/dist ./dist

EXPOSE 3000

CMD ["sh", "-c", "serve -s dist -l tcp://0.0.0.0:${PORT:-3000} --no-port-switching"]
