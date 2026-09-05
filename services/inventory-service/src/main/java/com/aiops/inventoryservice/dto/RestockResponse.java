package com.aiops.inventoryservice.dto;

/**
 * Body returned by POST /admin/restock. Carries before/after levels so the
 * caller (rca-agent's restock_inventory playbook) can record concrete
 * evidence of the change in its audit log rather than just "ok".
 */
public record RestockResponse(String productId, int previousQuantity, int newQuantity) {
}
