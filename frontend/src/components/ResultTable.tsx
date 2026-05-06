import './ResultTable.css';

interface Props {
  columns: string[];
  rows: Record<string, unknown>[];
}

export default function ResultTable({ columns, rows }: Props) {
  if (rows.length === 0) {
    return (
      <section className="result-table card fade-in">
        <div className="card-header">查询结果</div>
        <p className="result-table-empty">查询无结果</p>
      </section>
    );
  }

  return (
    <section className="result-table card fade-in">
      <div className="card-header">查询结果 ({rows.length} 行)</div>
      <div className="result-table-scroll">
        <table>
          <thead>
            <tr>
              {columns.map((col) => (
                <th key={col}>{col}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i}>
                {columns.map((col) => (
                  <td key={col}>{formatCell(row[col])}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function formatCell(value: unknown): string {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'number') {
    // Format as locale string if it looks like a float with decimals
    return Number.isInteger(value) ? value.toString() : value.toLocaleString();
  }
  return String(value);
}
