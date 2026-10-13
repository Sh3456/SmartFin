INSERT OR IGNORE INTO departments(department_id,department_name,business_unit) VALUES
(1,'Finance','Corporate Services'),(2,'IT Security','Technology'),(3,'Operations','Business Operations');
INSERT OR IGNORE INTO risk_categories(category_id,category_name,description) VALUES
(1,'Financial','Financial loss or reporting risk'),(2,'Operational','Process or service disruption'),
(3,'Compliance','Regulatory non-compliance'),(4,'Cybersecurity','Data or technology threat');
INSERT OR IGNORE INTO risks(risk_id,title,description,department_id,category_id,likelihood_score,impact_score,status,identified_date) VALUES
(1,'Supplier outage','A critical supplier interruption may delay service delivery.',3,2,4,4,'Open','2026-09-15'),
(2,'Unauthorized data access','Weak access controls could expose sensitive company data.',2,4,4,5,'Open','2026-09-18'),
(3,'Late regulatory filing','A missed deadline could result in penalties.',1,3,2,4,'Mitigated','2026-09-20'),
(4,'Budget overrun','Project costs may exceed the approved budget.',1,1,3,3,'Open','2026-09-22');
INSERT OR IGNORE INTO mitigation_controls(control_id,risk_id,control_title,owner_name,status,due_date,completion_date) VALUES
(1,1,'Qualify a backup supplier','Operations Manager','In Progress','2026-11-15',NULL),
(2,2,'Enforce multi-factor authentication','IT Security Lead','In Progress','2026-10-30',NULL),
(3,3,'Introduce filing calendar and review','Finance Controller','Completed','2026-09-25','2026-09-24'),
(4,4,'Monthly budget variance review','Finance Manager','Planned','2026-11-01',NULL);
