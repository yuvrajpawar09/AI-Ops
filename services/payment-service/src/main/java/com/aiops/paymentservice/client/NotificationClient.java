package com.aiops.paymentservice.client;

import com.aiops.paymentservice.dto.NotificationRequest;
import com.aiops.paymentservice.dto.NotificationResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;

@Component
public class NotificationClient {

    private static final Logger log = LoggerFactory.getLogger(NotificationClient.class);

    private final RestTemplate restTemplate;
    private final String notificationServiceUrl;

    public NotificationClient(RestTemplate restTemplate,
                               @Value("${services.notification.url}") String notificationServiceUrl) {
        this.restTemplate = restTemplate;
        this.notificationServiceUrl = notificationServiceUrl;
    }

    public NotificationResponse send(NotificationRequest request) {
        String endpoint = notificationServiceUrl + "/notifications";
        log.info("Calling notification-service at {}", endpoint);
        try {
            return restTemplate.postForObject(endpoint, request, NotificationResponse.class);
        } catch (RestClientException ex) {
            log.error("Call to notification-service failed: {}", ex.getMessage());
            throw ex;
        }
    }
}
