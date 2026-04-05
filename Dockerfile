FROM nikolaik/python-nodejs:python3.11-nodejs20

WORKDIR /app

# Copy root package files
COPY package*.json ./

# Copy ui package files
COPY ui/package*.json ./ui/

# Install root dependencies (express, ws, yaml, chokidar etc.)
RUN npm install

# Install UI dependencies
RUN cd ui && npm install

# Install Python requirements if and when needed (runner doesn't have a requirements.txt at the moment, but standard libs plus perhaps requests are used by local_micro_agent)
# Since local_micro_agent is in AGI, we should ensure the environment contains requests, pyyaml etc.
RUN pip install requests urllib3 qdrant-client pyyaml

# Copy all source code
COPY . .

# Build the UI statically
RUN cd ui && npm run build

# Expose port 5173
EXPOSE 5173

# Set default AGI_PATH for executions (it uses a peer directory normally, but in docker we can map it)
# By default, openminions expects agi-agent-kit at ../agi, or specified via AGI_PATH
ENV AGI_PATH="/agi-agent-kit"
ENV PORT=5173

CMD ["node", "bin/server.js"]
