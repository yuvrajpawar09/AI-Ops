package com.aiops.orderservice.config;

import com.aiops.orderservice.filter.TraceIdFilter;
import org.slf4j.MDC;
import org.springframework.boot.web.client.RestTemplateBuilder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.ClientHttpRequestInterceptor;
import org.springframework.web.client.RestTemplate;

import java.time.Duration;

@Configuration
public class RestTemplateConfig {

    /**
     * A single RestTemplate bean used for every outbound call this service makes
     * (to payment-service and inventory-service). The interceptor below is what
     * carries the traceId from this service's MDC onto the outgoing HTTP request,
     * so the next service can pick it up in its own TraceIdFilter.
     */
    @Bean
    public RestTemplate restTemplate(RestTemplateBuilder builder) {
        ClientHttpRequestInterceptor traceIdInterceptor = (request, body, execution) -> {
            String traceId = MDC.get(TraceIdFilter.MDC_TRACE_ID_KEY);
            if (traceId != null) {
                request.getHeaders().add(TraceIdFilter.TRACE_ID_HEADER, traceId);
            }
            return execution.execute(request, body);
        };

        return builder
                .setConnectTimeout(Duration.ofSeconds(3))
                .setReadTimeout(Duration.ofSeconds(5))
                .additionalInterceptors(traceIdInterceptor)
                .build();
    }
}
