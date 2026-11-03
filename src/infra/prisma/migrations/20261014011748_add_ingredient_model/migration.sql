-- CreateTable
CREATE TABLE `ingredients` (
    `id` CHAR(36) NOT NULL,
    `name` VARCHAR(100) NOT NULL,
    `unit` ENUM('KG', 'G', 'L', 'ML', 'UN') NOT NULL,
    `cost_per_unit` DECIMAL(10, 2) NOT NULL,
    `stock_quantity` DECIMAL(10, 3) NOT NULL DEFAULT 0,
    `stock_min` DECIMAL(10, 3) NOT NULL DEFAULT 0,
    `is_active` BOOLEAN NOT NULL DEFAULT true,
    `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updated_at` DATETIME(3) NOT NULL,
    `deleted_at` DATETIME(3) NULL,
    `unit_id` CHAR(36) NOT NULL,

    INDEX `ingredients_is_active_idx`(`is_active`),
    INDEX `ingredients_deleted_at_idx`(`deleted_at`),
    UNIQUE INDEX `ingredients_name_unit_id_key`(`name`, `unit_id`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- AddForeignKey
ALTER TABLE `ingredients` ADD CONSTRAINT `ingredients_unit_id_fkey` FOREIGN KEY (`unit_id`) REFERENCES `units`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;
