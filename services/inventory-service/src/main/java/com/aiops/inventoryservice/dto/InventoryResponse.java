package com.aiops.inventoryservice.dto;

/** Body returned by POST /inventory/reserve. status is "RESERVED" or "OUT_OF_STOCK". */
public record InventoryResponse(String reservationId, String orderId, String status) {
}
