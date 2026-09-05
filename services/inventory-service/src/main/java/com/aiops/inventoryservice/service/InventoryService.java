package com.aiops.inventoryservice.service;

import com.aiops.inventoryservice.dto.InventoryRequest;
import com.aiops.inventoryservice.dto.InventoryResponse;
import jakarta.annotation.PostConstruct;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class InventoryService {

    private static final Logger log = LoggerFactory.getLogger(InventoryService.class);

    // Phase 1 has no database - stock levels live in memory and reset on restart.
    private final Map<String, Integer> stock = new ConcurrentHashMap<>();

    @PostConstruct
    void seedStock() {
        // Stock never restocks (no DB, no replenishment job in Phase 1), so
        // PROD-1/PROD-2 are seeded high enough to survive realistic repeated
        // testing and Phase 3 training-traffic generation (tens to low
        // hundreds of orders) without silently running dry mid-run - that
        // previously turned "normal" training traffic into a wall of
        // OUT_OF_STOCK failures once the original seed (50) was exhausted.
        // PROD-3 stays deliberately scarce so /orders can still be used to
        // demonstrate the OUT_OF_STOCK failure path on purpose.
        stock.put("PROD-1", 100_000);
        stock.put("PROD-2", 100_000);
        stock.put("PROD-3", 2);
        log.info("Seeded inventory: {}", stock);
    }

    public InventoryResponse reserve(InventoryRequest request) {
        String productId = request.productId();
        int quantity = request.quantity();

        // compute() runs atomically per key, so concurrent reservations for the
        // same product can't both read the same stale stock count and oversell.
        boolean[] reserved = {false};
        stock.compute(productId, (id, currentStock) -> {
            int available = currentStock == null ? 0 : currentStock;
            if (available >= quantity) {
                reserved[0] = true;
                return available - quantity;
            }
            return available;
        });

        if (reserved[0]) {
            String reservationId = UUID.randomUUID().toString();
            log.info("Reserved {} units of {} for order {} (reservationId={})",
                    quantity, productId, request.orderId(), reservationId);
            return new InventoryResponse(reservationId, request.orderId(), "RESERVED");
        }

        log.warn("Insufficient stock for {} (requested={}) - order {} rejected",
                productId, quantity, request.orderId());
        return new InventoryResponse(null, request.orderId(), "OUT_OF_STOCK");
    }
}
