# Stage 1: Build the frontend
FROM node:20-alpine AS build-stage
WORKDIR /app
COPY ./e-safari-ui .
RUN npm install && npm run build

# Stage 2: Serve with nginx
FROM nginx:1.25-alpine
# Optional: remove default config if you're replacing it
# RUN rm /etc/nginx/conf.d/default.conf
# Copy your custom nginx config
# COPY ./nginx/default.conf /etc/nginx/conf.d/default.conf
# Copy built frontend
COPY --from=build-stage /app/build /usr/share/nginx/html