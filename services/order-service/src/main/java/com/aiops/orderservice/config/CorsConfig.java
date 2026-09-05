package com.aiops.orderservice.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * The Phase 5 dashboard runs in the browser at http://localhost:3000 and
 * calls this service's published port (http://localhost:8081) directly -
 * that's a cross-origin request by the browser's same-origin policy, even
 * though both ultimately run on the same laptop. Without this, the
 * dashboard's "Trigger" buttons would fail silently with a CORS error and
 * nothing else in this service would look wrong.
 */
@Configuration
public class CorsConfig {

    @Bean
    public WebMvcConfigurer corsConfigurer() {
        return new WebMvcConfigurer() {
            @Override
            public void addCorsMappings(CorsRegistry registry) {
                registry.addMapping("/**")
                        .allowedOrigins("*")
                        .allowedMethods("GET", "POST", "PUT", "DELETE", "OPTIONS");
            }
        };
    }
}
