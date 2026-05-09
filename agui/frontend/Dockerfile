FROM node:20-slim AS builder

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

FROM nginx:alpine
# Copy built static files to nginx default directory
COPY --from=builder /app/dist /usr/share/nginx/html

# Optional: if you need a custom nginx configuration for React router (SPA fallback)
# you can copy it here, but Vite standard build works natively with root `/` for base routes.

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
