-- 1. Critical risks
SELECT risk_id,title,risk_score,status FROM risks
WHERE status <> 'Closed' AND risk_score >= 17 ORDER BY risk_score DESC;

-- 2. Department exposure: JOIN + GROUP BY
SELECT d.department_name,COUNT(r.risk_id) active_risks,
       COALESCE(SUM(r.risk_score),0) exposure,
       SUM(CASE WHEN r.risk_score>=17 THEN 1 ELSE 0 END) critical_risks
FROM departments d LEFT JOIN risks r
ON r.department_id=d.department_id AND r.status<>'Closed'
GROUP BY d.department_id,d.department_name ORDER BY exposure DESC;

-- 3. HAVING: departments with more than one active risk
SELECT d.department_name,COUNT(*) active_risks FROM departments d
JOIN risks r ON r.department_id=d.department_id WHERE r.status<>'Closed'
GROUP BY d.department_id,d.department_name HAVING COUNT(*)>1;

-- 4. Window function: risk rank inside each department
SELECT d.department_name,r.title,r.risk_score,
       RANK() OVER(PARTITION BY d.department_name ORDER BY r.risk_score DESC) department_rank
FROM risks r JOIN departments d ON d.department_id=r.department_id
WHERE r.status<>'Closed';

-- 5. Mitigation completion summary
SELECT COUNT(*) total_controls,
       SUM(CASE WHEN status='Completed' THEN 1 ELSE 0 END) completed_controls
FROM mitigation_controls;
