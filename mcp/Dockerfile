FROM python:3.12-slim

WORKDIR /app

RUN addgroup --system mcp && adduser --system --ingroup mcp mcp

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chown -R mcp:mcp /app
USER mcp

CMD ["python", "server.py"]
