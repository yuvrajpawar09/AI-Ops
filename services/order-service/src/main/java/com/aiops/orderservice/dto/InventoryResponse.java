package com.aiops.orderservice.dto;

/** What inventory-service's POST /inventory/reserve replies with. status is "RESERVED" or "OUT_OF_STOCK". */
public record InventoryResponse(String reservationId, String orderId, String status) {
}
