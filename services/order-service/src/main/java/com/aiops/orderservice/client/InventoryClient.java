package com.aiops.orderservice.client;

import com.aiops.orderservice.dto.InventoryRequest;
import com.aiops.orderservice.dto.InventoryResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;

@Component
public class InventoryClient {

    private static final Logger log = LoggerFactory.getLogger(InventoryClient.class);

    private final RestTemplate restTemplate;
    private final String inventoryServiceUrl;

    public InventoryClient(RestTemplate restTemplate, @Value("${services.inventory.url}") String inventoryServiceUrl) {
        this.restTemplate = restTemplate;
        this.inventoryServiceUrl = inventoryServiceUrl;
    }

    public InventoryResponse reserve(InventoryRequest request) {
        String endpoint = inventoryServiceUrl + "/inventory/reserve";
        log.info("Calling inventory-service at {}", endpoint);
        try {
            return restTemplate.postForObject(endpoint, request, InventoryResponse.class);
        } catch (RestClientException ex) {
            log.error("Call to inventory-service failed: {}", ex.getMessage());
            throw ex;
        }
    }
}
