package com.aiops.orderservice.client;

import com.aiops.orderservice.dto.PaymentRequest;
import com.aiops.orderservice.dto.PaymentResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;

@Component
public class PaymentClient {

    private static final Logger log = LoggerFactory.getLogger(PaymentClient.class);

    private final RestTemplate restTemplate;
    private final String paymentServiceUrl;

    public PaymentClient(RestTemplate restTemplate, @Value("${services.payment.url}") String paymentServiceUrl) {
        this.restTemplate = restTemplate;
        this.paymentServiceUrl = paymentServiceUrl;
    }

    public PaymentResponse charge(PaymentRequest request) {
        String endpoint = paymentServiceUrl + "/payments";
        log.info("Calling payment-service at {}", endpoint);
        try {
            return restTemplate.postForObject(endpoint, request, PaymentResponse.class);
        } catch (RestClientException ex) {
            log.error("Call to payment-service failed: {}", ex.getMessage());
            throw ex;
        }
    }
}
