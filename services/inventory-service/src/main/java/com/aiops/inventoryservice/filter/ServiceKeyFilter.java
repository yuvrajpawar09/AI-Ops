package com.aiops.inventoryservice.filter;

import jakarta.annotation.PostConstruct;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.List;
import java.util.Set;

/**
 * Phase 8: /admin/restock and /admin/inventory are the actuation and inspection
 * surface auto-remediation writes to, so they are no longer open. Only callers
 * presenting the shared SERVICE_API_KEY may reach them; /inventory/reserve stays
 * open because order-service calls it as part of the normal request path.
 */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE + 10)
public class ServiceKeyFilter extends OncePerRequestFilter {

    public static final String HEADER = "X-Service-Key";

    private static final Logger log = LoggerFactory.getLogger(ServiceKeyFilter.class);

    private static final Set<String> PLACEHOLDER_EXACT = Set.of("", "secret", "admin", "password", "todo", "xxx");

    private static final List<String> PLACEHOLDER_FRAGMENTS = List.of(
            "change-me", "change_me", "changeme", "replace-me", "replace_me", "replaceme",
            "placeholder", "your-secret", "your-password", "example", "xxxx");

    private static final int MIN_LENGTH = 16;

    private final String serviceApiKey;

    public ServiceKeyFilter(@Value("${security.service-api-key:}") String serviceApiKey) {
        this.serviceApiKey = serviceApiKey == null ? "" : serviceApiKey.trim();
    }

    @PostConstruct
    void validate() {
        if (isPlaceholder(serviceApiKey)) {
            throw new IllegalStateException(
                    "SERVICE_API_KEY is missing or still a placeholder. Copy .env.example to .env "
                            + "and set a real value before starting inventory-service.");
        }
        if (serviceApiKey.length() < MIN_LENGTH) {
            throw new IllegalStateException(
                    "SERVICE_API_KEY is only " + serviceApiKey.length() + " characters; at least "
                            + MIN_LENGTH + " are required.");
        }
        log.info("Service key loaded; /admin/** requires the {} header", HEADER);
    }

    private static boolean isPlaceholder(String value) {
        String lowered = value.toLowerCase();
        if (PLACEHOLDER_EXACT.contains(lowered)) {
            return true;
        }
        return PLACEHOLDER_FRAGMENTS.stream().anyMatch(lowered::contains);
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        return !request.getRequestURI().startsWith("/admin");
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {

        String provided = request.getHeader(HEADER);
        if (provided == null || provided.isBlank()) {
            log.warn("Rejected {} {} - no {} header", request.getMethod(), request.getRequestURI(), HEADER);
            deny(response, HttpServletResponse.SC_UNAUTHORIZED, "Missing " + HEADER + " header.");
            return;
        }

        boolean matches = MessageDigest.isEqual(
                provided.trim().getBytes(StandardCharsets.UTF_8),
                serviceApiKey.getBytes(StandardCharsets.UTF_8));

        if (!matches) {
            log.warn("Rejected {} {} - invalid {}", request.getMethod(), request.getRequestURI(), HEADER);
            deny(response, HttpServletResponse.SC_FORBIDDEN, "Invalid " + HEADER + ".");
            return;
        }

        chain.doFilter(request, response);
    }

    private void deny(HttpServletResponse response, int statusCode, String message) throws IOException {
        response.setStatus(statusCode);
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        response.getWriter().write("{\"error\":\"" + message + "\"}");
    }
}
