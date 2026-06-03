# Stage 1: Build e-safari-ui (root app)
FROM node:20-alpine AS e_safari_build
WORKDIR /app
COPY ./e-safari-ui/package*.json ./
RUN npm install
COPY ./e-safari-ui ./
RUN npm run build

# Stage 2: Build afri-met (served under /afri-met/)
# FROM node:20-alpine AS afri_met_build
# WORKDIR /app
# COPY ./afri-met/package*.json ./
# RUN npm install
# COPY ./afri-met ./
# RUN npm run build -- --base=/afri-met/

# stage 3: build multi-hazard-ui (served under /multi-hazard/)
FROM node:20-alpine AS multi_hazard_build
WORKDIR /app
COPY ./multi-hazard-ui/package*.json ./
RUN npm install
COPY ./multi-hazard-ui ./
RUN npm run build

# Stage 3: Serve static apps with nginx
FROM nginx:1.25-alpine
COPY --from=e_safari_build /app/build /usr/share/nginx/html
# COPY --from=afri_met_build /app/dist /usr/share/nginx/afri-met
COPY --from=multi_hazard_build /app/dist /usr/share/nginx/multi-hazard-ui