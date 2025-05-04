import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NgChartsModule } from 'ng2-charts';
import { ChartType, ChartOptions, ChartData } from 'chart.js';
import { Hl7Service, StatPoint } from '../services/hl7.service';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-stats',
  standalone: true,
  imports: [CommonModule, NgChartsModule, FormsModule],
  templateUrl: './stats.component.html',
  styleUrls: ['./stats.component.scss']
})
export class StatsComponent implements OnInit {
  stats: StatPoint[] = [];
  error: string | null = null;

  startDate: string = '';
  endDate: string = '';

  chartData: ChartData<ChartType> = {
    labels: [],
    datasets: [
      {
        label: 'Messages HL7 traités',
        data: [],
        borderColor: '#2e3b8e',
        tension: 0.3,
        fill: false
      }
    ]
  };
  
  chartOptions: ChartOptions<ChartType> = {
    responsive: true,
    plugins: {
      legend: {
        display: true,
        position: 'bottom'
      }
    }
  };
  

  chartType: ChartType = 'line';

  constructor(private hl7: Hl7Service) {}

  ngOnInit(): void {
    // Tu peux charger toutes les stats initialement OU attendre que l'utilisateur choisisse
  }

  exportExcel(): void {
    this.hl7.exportStatsExcel(); // À adapter si besoin de passer dates aussi
  }

  loadStats(): void {
    if (!this.startDate || !this.endDate) {
      this.error = "Veuillez sélectionner la date de début et de fin.";
      return;
    }

    if (this.startDate > this.endDate) {
      this.error = "La date de début doit être antérieure à la date de fin.";
      return;
    }

    this.error = null;

    this.hl7.getStatsBetweenDates(this.startDate, this.endDate).subscribe({
      next: (points: StatPoint[]) => {
        this.stats = points;
        this.chartData.labels = points.map(p =>
          new Date(p.period).toLocaleString('fr-FR', {
            day: '2-digit',
            month: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
          })
        );
        this.chartData.datasets[0].data = points.map(p => p.count);
      },
      error: (err: any) => {
        console.error('Erreur récupération stats HL7', err);
        this.error = 'Erreur lors de la récupération des statistiques.';
      }
    });
  }
}
