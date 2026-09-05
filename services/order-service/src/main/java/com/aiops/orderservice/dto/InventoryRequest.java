package com.aiops.orderservice.dto;

/** What order-service sends to inventory-service's POST /inventory/reserve. */
public record InventoryRequest(String orderId, String productId, int quantity) {
}
