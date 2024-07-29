DELIMITER //

CREATE PROCEDURE generate_combinations()
BEGIN
    DECLARE done INT DEFAULT 0;
    DECLARE tipo_id INT;
    DECLARE tipo_nombre VARCHAR(255);
    DECLARE color_id INT;
    DECLARE material_id INT;
    DECLARE agregado_id INT;
    DECLARE agregado_nombre VARCHAR(255);
    DECLARE tipo_keyword VARCHAR(255);

    DECLARE tipo_cursor CURSOR FOR SELECT id, nombre FROM tipos;
    DECLARE color_cursor CURSOR FOR SELECT id FROM colores;
    DECLARE material_cursor CURSOR FOR SELECT id FROM materiales;
    DECLARE agregado_cursor CURSOR FOR SELECT id, tipo FROM agregados;

    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = 1;

    OPEN tipo_cursor;

    tipo_loop: LOOP
        FETCH tipo_cursor INTO tipo_id, tipo_nombre;
        IF done THEN
            LEAVE tipo_loop;
        END IF;

        -- Obtener la primera palabra del nombre del tipo
        -- SET tipo_keyword = LEFT(tipo_nombre, LOCATE(' ', tipo_nombre) - 1);

        -- Obtener la primera palabra del nombre del tipo
        SET tipo_keyword = IF(LOCATE(' ', tipo_nombre) = 0, tipo_nombre, LEFT(tipo_nombre, LOCATE(' ', tipo_nombre) - 1));


        SET done = 0;
        OPEN color_cursor;

        color_loop: LOOP
            FETCH color_cursor INTO color_id;
            IF done THEN
                LEAVE color_loop;
            END IF;

            SET done = 0;
            OPEN material_cursor;

            material_loop: LOOP
                FETCH material_cursor INTO material_id;
                IF done THEN
                    LEAVE material_loop;
                END IF;

                -- Combinaciones con agregados relacionados
                SET done = 0;
                OPEN agregado_cursor;

                agregado_loop: LOOP
                    FETCH agregado_cursor INTO agregado_id, agregado_nombre;
                    IF done THEN
                        LEAVE agregado_loop;
                    END IF;

                    -- Insertar solo si el agregado es relevante para el tipo
                    IF LOCATE(tipo_keyword, agregado_nombre) = 1 THEN
                        INSERT INTO producto_combinaciones (tipo_id, color_id, material_id, agregado_id, stock, precioU)
                        VALUES (tipo_id, color_id, material_id, agregado_id, 0, 0);
                    END IF;

                END LOOP agregado_loop;
                CLOSE agregado_cursor;

                -- Combinaciones sin agregados
                INSERT INTO producto_combinaciones (tipo_id, color_id, material_id, agregado_id, stock, precioU)
                VALUES (tipo_id, color_id, material_id, NULL, 0, 0);

                SET done = 0;
            END LOOP material_loop;
            CLOSE material_cursor;
            SET done = 0;
        END LOOP color_loop;
        CLOSE color_cursor;
        SET done = 0;
    END LOOP tipo_loop;

    CLOSE tipo_cursor;
END //

DELIMITER ;
