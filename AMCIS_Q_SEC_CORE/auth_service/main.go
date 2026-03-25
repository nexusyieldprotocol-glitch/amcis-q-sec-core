// AMCIS Authentication Service
// Post-quantum ready OAuth2/OIDC implementation

package main

import (
	"context"
	"crypto/ed25519"
	"crypto/rand"
	"crypto/sha512"
	"fmt"
	"log"
	"net"
	"time"

	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
	"golang.org/x/crypto/argon2"
)

// TokenConfig holds JWT configuration
type TokenConfig struct {
	AccessTokenTTL  time.Duration
	RefreshTokenTTL time.Duration
	Issuer          string
	Audience        string
}

// DefaultConfig returns default token configuration
func DefaultConfig() TokenConfig {
	return TokenConfig{
		AccessTokenTTL:  15 * time.Minute,
		RefreshTokenTTL: 24 * time.Hour,
		Issuer:          "amcis-auth",
		Audience:        "amcis-api",
	}
}

// User represents an authenticated user
type User struct {
	ID       string
	Username string
	Email    string
	Roles    []string
}

// TokenPair contains access and refresh tokens
type TokenPair struct {
	AccessToken  string
	RefreshToken string
	ExpiresIn    int64
	TokenType    string
}

// PQSigner implements hybrid signature (Ed25519 + placeholder for Dilithium)
type PQSigner struct {
	classical ed25519.PrivateKey
	publicKey ed25519.PublicKey
}

// NewPQSigner creates a new hybrid signer
func NewPQSigner() (*PQSigner, error) {
	pub, priv, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		return nil, fmt.Errorf("failed to generate Ed25519 key: %w", err)
	}

	return &PQSigner{
		classical: priv,
		publicKey: pub,
	}, nil
}

// Sign creates a hybrid signature
// In production, this would also include Dilithium signature
func (s *PQSigner) Sign(data []byte) []byte {
	h := sha512.Sum512(data)
	
	// Ed25519 signature
	sig1 := ed25519.Sign(s.classical, h[:])
	
	// Placeholder: In production, add Dilithium signature here
	// sig2 := dilithium.Sign(...)
	
	// For now, just return Ed25519 signature
	// In production: return append(sig1, sig2...)
	return sig1
}

// Verify verifies a hybrid signature
func (s *PQSigner) Verify(data, signature []byte) bool {
	h := sha512.Sum512(data)
	return ed25519.Verify(s.publicKey, h[:], signature)
}

// AuthService handles authentication
type AuthService struct {
	config    TokenConfig
	signer    *PQSigner
	users     map[string]*User
	passwords map[string]string // username -> hashed password
}

// NewAuthService creates a new authentication service
func NewAuthService(config TokenConfig) (*AuthService, error) {
	signer, err := NewPQSigner()
	if err != nil {
		return nil, err
	}

	service := &AuthService{
		config:    config,
		signer:    signer,
		users:     make(map[string]*User),
		passwords: make(map[string]string),
	}

	// Add a test user
	service.RegisterUser("admin", "admin@amcis.local", "secure_password_123", []string{"admin"})

	return service, nil
}

// RegisterUser registers a new user
func (s *AuthService) RegisterUser(username, email, password string, roles []string) error {
	if _, exists := s.users[username]; exists {
		return fmt.Errorf("user already exists")
	}

	// Hash password with Argon2
	hash := s.hashPassword(password)

	user := &User{
		ID:       uuid.New().String(),
		Username: username,
		Email:    email,
		Roles:    roles,
	}

	s.users[username] = user
	s.passwords[username] = hash

	return nil
}

// hashPassword hashes a password using Argon2
func (s *AuthService) hashPassword(password string) string {
	salt := make([]byte, 16)
	rand.Read(salt)

	hash := argon2.IDKey([]byte(password), salt, 3, 64*1024, 4, 32)
	
	// Store salt + hash
	result := make([]byte, len(salt)+len(hash))
	copy(result, salt)
	copy(result[len(salt):], hash)

	return string(result)
}

// verifyPassword verifies a password against a hash
func (s *AuthService) verifyPassword(password, hash string) bool {
	if len(hash) < 16 {
		return false
	}

	salt := []byte(hash[:16])
	expectedHash := []byte(hash[16:])

	actualHash := argon2.IDKey([]byte(password), salt, 3, 64*1024, 4, 32)

	// Constant-time comparison
	if len(actualHash) != len(expectedHash) {
		return false
	}

	var result byte
	for i := range actualHash {
		result |= actualHash[i] ^ expectedHash[i]
	}

	return result == 0
}

// Authenticate validates credentials and returns a user
func (s *AuthService) Authenticate(username, password string) (*User, error) {
	user, exists := s.users[username]
	if !exists {
		return nil, fmt.Errorf("invalid credentials")
	}

	hash := s.passwords[username]
	if !s.verifyPassword(password, hash) {
		return nil, fmt.Errorf("invalid credentials")
	}

	return user, nil
}

// GenerateTokens creates access and refresh tokens for a user
func (s *AuthService) GenerateTokens(user *User) (*TokenPair, error) {
	now := time.Now()

	// Create access token claims
	accessClaims := jwt.MapClaims{
		"sub":   user.ID,
		"name":  user.Username,
		"email": user.Email,
		"roles": user.Roles,
		"iss":   s.config.Issuer,
		"aud":   s.config.Audience,
		"iat":   now.Unix(),
		"exp":   now.Add(s.config.AccessTokenTTL).Unix(),
		"jti":   uuid.New().String(),
	}

	accessToken := jwt.NewWithClaims(jwt.SigningMethodEdDSA, accessClaims)
	accessToken.Header["kid"] = "pq-key-1"
	accessToken.Header["alg"] = "EdDSA"
	// Add PQ indicator
	accessToken.Header["pq"] = true

	accessString, err := accessToken.SignedString(s.signer.classical)
	if err != nil {
		return nil, fmt.Errorf("failed to sign access token: %w", err)
	}

	// Create refresh token
	refreshClaims := jwt.MapClaims{
		"sub": user.ID,
		"iss": s.config.Issuer,
		"iat": now.Unix(),
		"exp": now.Add(s.config.RefreshTokenTTL).Unix(),
		"jti": uuid.New().String(),
		"typ": "refresh",
	}

	refreshToken := jwt.NewWithClaims(jwt.SigningMethodEdDSA, refreshClaims)
	refreshString, err := refreshToken.SignedString(s.signer.classical)
	if err != nil {
		return nil, fmt.Errorf("failed to sign refresh token: %w", err)
	}

	return &TokenPair{
		AccessToken:  accessString,
		RefreshToken: refreshString,
		ExpiresIn:    int64(s.config.AccessTokenTTL.Seconds()),
		TokenType:    "Bearer",
	}, nil
}

// ValidateToken validates and parses a JWT token
func (s *AuthService) ValidateToken(tokenString string) (*jwt.MapClaims, error) {
	token, err := jwt.Parse(tokenString, func(token *jwt.Token) (interface{}, error) {
		// Validate signing method
		if _, ok := token.Method.(*jwt.SigningMethodEd25519); !ok {
			return nil, fmt.Errorf("unexpected signing method: %v", token.Header["alg"])
		}
		return s.signer.publicKey, nil
	})

	if err != nil {
		return nil, fmt.Errorf("token validation failed: %w", err)
	}

	if claims, ok := token.Claims.(jwt.MapClaims); ok && token.Valid {
		return &claims, nil
	}

	return nil, fmt.Errorf("invalid token claims")
}

// RefreshTokens creates new tokens using a refresh token
func (s *AuthService) RefreshTokens(refreshToken string) (*TokenPair, error) {
	claims, err := s.ValidateToken(refreshToken)
	if err != nil {
		return nil, err
	}

	// Verify it's a refresh token
	if typ, ok := (*claims)["typ"].(string); !ok || typ != "refresh" {
		return nil, fmt.Errorf("invalid token type")
	}

	// Get user
	userID := (*claims)["sub"].(string)
	
	// Find user by ID
	var user *User
	for _, u := range s.users {
		if u.ID == userID {
			user = u
			break
		}
	}

	if user == nil {
		return nil, fmt.Errorf("user not found")
	}

	return s.GenerateTokens(user)
}

// AuthorizationMiddleware creates a middleware for authorization
func (s *AuthService) AuthorizationMiddleware(requiredRoles []string) func(string) error {
	return func(tokenString string) error {
		claims, err := s.ValidateToken(tokenString)
		if err != nil {
			return err
		}

		// Check roles
		userRoles, ok := (*claims)["roles"].([]interface{})
		if !ok {
			return fmt.Errorf("no roles in token")
		}

		roleMap := make(map[string]bool)
		for _, r := range userRoles {
			if role, ok := r.(string); ok {
				roleMap[role] = true
			}
		}

		for _, required := range requiredRoles {
			if !roleMap[required] {
				return fmt.Errorf("missing required role: %s", required)
			}
		}

		return nil
	}
}

func main() {
	config := DefaultConfig()
	
	authService, err := NewAuthService(config)
	if err != nil {
		log.Fatalf("Failed to create auth service: %v", err)
	}

	// Example: Authenticate and generate tokens
	user, err := authService.Authenticate("admin", "secure_password_123")
	if err != nil {
		log.Fatalf("Authentication failed: %v", err)
	}

	log.Printf("User authenticated: %s (%s)", user.Username, user.Email)

	tokens, err := authService.GenerateTokens(user)
	if err != nil {
		log.Fatalf("Token generation failed: %v", err)
	}

	log.Printf("Access token generated (expires in %d seconds)", tokens.ExpiresIn)

	// Validate the token
	claims, err := authService.ValidateToken(tokens.AccessToken)
	if err != nil {
		log.Fatalf("Token validation failed: %v", err)
	}

	log.Printf("Token validated for user: %s", (*claims)["name"])

	log.Println("Auth service initialized successfully")
}
