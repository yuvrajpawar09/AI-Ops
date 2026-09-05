package com.aiops.orderservice.filter;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.ServletRequest;
import jakarta.servlet.ServletResponse;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.MDC;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.UUID;

/**
 * Reads (or generates) a traceId for every incoming HTTP request and stores it
 * in SLF4J's MDC. Logback picks up MDC entries automatically and adds them as
 * fields in the JSON log output, so every log line written while handling this
 * request carries the same traceId - that's what lets us stitch together log
 * lines from order-service, payment-service, inventory-service and
 * notification-service into a single causal chain later in Phase 5 (RCA agent).
 */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class TraceIdFilter extends OncePerRequestFilter {

    public static final String TRACE_ID_HEADER = "X-Trace-Id";
    public static final String MDC_TRACE_ID_KEY = "traceId";

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {

        String traceId = request.getHeader(TRACE_ID_HEADER);
        if (traceId == null || traceId.isBlank()) {
            // No incoming traceId means this service is the entry point of the flow.
            traceId = UUID.randomUUID().toString();
        }

        try {
            MDC.put(MDC_TRACE_ID_KEY, traceId);
            response.setHeader(TRACE_ID_HEADER, traceId);
            chain.doFilter(request, response);
        } finally {
            // MDC is thread-local and Tomcat reuses worker threads across requests,
            // so it must be cleared or the next request on this thread would leak
            // this traceId into its logs.
            MDC.remove(MDC_TRACE_ID_KEY);
        }
    }
}
