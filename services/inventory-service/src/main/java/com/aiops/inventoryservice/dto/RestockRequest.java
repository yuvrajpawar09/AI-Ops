package com.aiops.inventoryservice.dto;

/** Body of POST /admin/restock. */
public record RestockRequest(String productId, int quantity) {
}
