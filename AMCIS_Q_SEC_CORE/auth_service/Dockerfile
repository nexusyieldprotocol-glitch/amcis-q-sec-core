# Multi-stage build for AMCIS Auth Service
FROM golang:1.21-bookworm AS builder

WORKDIR /app

# Copy go mod files
COPY go.mod go.sum ./
RUN go mod download

# Copy source
COPY *.go ./

# Build
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o amcis-auth-service .

# Runtime stage
FROM gcr.io/distroless/static:nonroot

WORKDIR /

# Copy binary
COPY --from=builder /app/amcis-auth-service /usr/local/bin/

# Use nonroot user
USER nonroot:nonroot

EXPOSE 50052

ENTRYPOINT ["/usr/local/bin/amcis-auth-service"]
