package com.aiops.inventoryservice.dto;

/** Body of POST /inventory/reserve, sent by order-service. */
public record InventoryRequest(String orderId, String productId, int quantity) {
}
