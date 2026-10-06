package com.aiops.inventoryservice.controller;

import com.aiops.inventoryservice.dto.RestockRequest;
import com.aiops.inventoryservice.dto.RestockResponse;
import com.aiops.inventoryservice.service.InventoryService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * Phase 6: the actuation surface for the restock_inventory playbook, and a
 * read endpoint for inspecting stock during a demo. Phase 8 put the same auth
 * boundary in front of it as order-service's /admin/config - ServiceKeyFilter
 * requires the shared SERVICE_API_KEY on every /admin/** request. The audit
 * trail still lives on the caller side in rca-agent's remediationLog.
 */
@RestController
@RequestMapping("/admin")
public class AdminInventoryController {

    private final InventoryService inventoryService;

    public AdminInventoryController(InventoryService inventoryService) {
        this.inventoryService = inventoryService;
    }

    @GetMapping("/inventory")
    public ResponseEntity<Map<String, Integer>> currentInventory() {
        return ResponseEntity.ok(inventoryService.currentStock());
    }

    @PostMapping("/restock")
    public ResponseEntity<RestockResponse> restock(@RequestBody RestockRequest request) {
        if (request.productId() == null || request.productId().isBlank() || request.quantity() <= 0) {
            return ResponseEntity.badRequest().build();
        }
        int[] beforeAfter = inventoryService.restock(request.productId(), request.quantity());
        return ResponseEntity.ok(
                new RestockResponse(request.productId(), beforeAfter[0], beforeAfter[1]));
    }
}
