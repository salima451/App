import {
  Component,
  OnInit,
  ChangeDetectionStrategy
} from '@angular/core';

import { WebSocketService } from '../services/websocket.service';
import { Hl7Service } from '../services/hl7.service';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { NgApexchartsModule } from 'ng-apexcharts';
import {
  ApexAxisChartSeries,
  ApexChart,
  ApexXAxis,
  ApexTitleSubtitle
} from 'ng-apexcharts';

import { formatDate } from '@angular/common';

export type ChartOptions = {
  series: ApexAxisChartSeries;
  chart: ApexChart;
  xaxis: ApexXAxis;
  title: ApexTitleSubtitle;
};

@Component({
  standalone: true,
  selector: 'app-tableaudebord',
  templateUrl: './tableaudebord.component.html',
  styleUrls: ['./tableaudebord.component.scss'],
  imports: [CommonModule, FormsModule, NgApexchartsModule],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class TableaubordComponent implements OnInit {
  public chartOptions: ChartOptions = {
    series: [],
    chart: { type: 'line' },
    title: { text: '' },
    xaxis: { categories: [] }
  };

  public unitChartOptions: ChartOptions = {
    series: [],
    chart: { type: 'bar' },
    title: { text: '' },
    xaxis: { categories: [] }
  };    // patients par unité
  public data: any[] = [];
  public startDate!: string;
  public endDate!: string;
  public startHour!: string;
  public endHour!: string;
  constructor(
    private hl7: Hl7Service,
    private wsService: WebSocketService
  ) {}

  ngOnInit(): void {
    this.loadChartData();
    this.subscribeToWebSocket();
  }

  private loadChartData(): void {
    const today = new Date();
    const start = formatDate(new Date(today.getTime() - 29 * 86400000), 'yyyy-MM-dd', 'en');
    const end = formatDate(today, 'yyyy-MM-dd', 'en');

    this.hl7.getPatientCountsAdvanced(start, end).subscribe((res) => {
      const dailyCounts = res.daily_counts;

      const hours = dailyCounts[0].hourly_counts.map((h: any) => h.hour);

      // 1. Graphique ligne (total patients)
      const globalSeries = dailyCounts.map((day: any) => {
        return {
          name: day.date,
          data: day.hourly_counts.map((h: any) => h.total_patients)
        };
      });

      // 2. Graphique barres empilées (par unité)
      const allUnits = new Set<string>();

      // 1. Extraire tous les noms d’unités présents dans les données
      dailyCounts.forEach((day:any)=> {
        day.hourly_counts.forEach((h: any) => {
          const units = Object.keys(h.by_unit || {});
          units.forEach(unit => allUnits.add(unit));
        });
      });

      // 2. Construire les séries empilées
      const unitSeries: ApexAxisChartSeries = [];

      allUnits.forEach(unit => {
        const unitData: number[] = [];

        dailyCounts.forEach((day:any) => {
          day.hourly_counts.forEach((h: any) => {
            unitData.push(h.by_unit?.[unit] || 0); // plus sécurisé avec ?. et fallback 0
          });
        });

        unitSeries.push({
          name: unit,
          data: unitData
        });
      });


      this.chartOptions = {
        series: globalSeries,
        chart: {
          type: 'line',
          height: 450,
          zoom: { enabled: true }
        },
        title: {
          text: 'Total de patients par heure (par jour)'
        },
        xaxis: {
          categories: hours
        }
      };

      this.unitChartOptions = {
        series: unitSeries,
        chart: {
          type: 'bar',
          stacked: true,
          height: 450
        },
        title: {
          text: 'Répartition par unité de soins (toutes heures)'
        },
        xaxis: {
          categories: Array.from({ length: dailyCounts.length * 24 }, (_, i) => {
            const d = dailyCounts[Math.floor(i / 24)].date;
            const h = hours[i % 24];
            return `${d} ${h}`;
          })
        }
      };
    });
  }
  private prepareCharts(dailyCounts: any[]): void {
    const hours = dailyCounts[0].hourly_counts.map((h: any) => h.hour);

    const globalSeries = dailyCounts.map((day: any) => ({
      name: day.date,
      data: day.hourly_counts.map((h: any) => h.total_patients)
    }));

    const allUnits = new Set<string>();
    dailyCounts.forEach((day: any) => {
      day.hourly_counts.forEach((h: any) => {
        Object.keys(h.by_unit || {}).forEach(u => allUnits.add(u));
      });
    });

    const unitSeries: ApexAxisChartSeries = [];
    allUnits.forEach(unit => {
      const unitData: number[] = [];
      dailyCounts.forEach((day: any) => {
        day.hourly_counts.forEach((h: any) => {
          unitData.push(h.by_unit?.[unit] || 0);
        });
      });
      unitSeries.push({ name: unit, data: unitData });
    });

    this.chartOptions = {
      series: globalSeries,
      chart: { type: 'line', height: 450, zoom: { enabled: true } },
      title: { text: 'Total de patients par heure (par jour)' },
      xaxis: { categories: hours }
    };

    this.unitChartOptions = {
      series: unitSeries,
      chart: { type: 'bar', stacked: true, height: 450 },
      title: { text: 'Répartition par unité de soins (toutes heures)' },
      xaxis: {
        categories: Array.from({ length: dailyCounts.length * 24 }, (_, i) => {
          const d = dailyCounts[Math.floor(i / 24)].date;
          const h = hours[i % 24];
          return `${d} ${h}`;
        })
      }
    };
  }

  onAfficherVolumetrie(): void {
    console.log("➡ Affichage demandé pour : ", this.startDate, this.endDate, this.startHour, this.endHour);

    const start = this.startDate;
    const end = this.endDate;

    if (!start || !end) {
      console.warn('Dates non renseignées.');
      return;
    }

    this.hl7.getPatientCountsAdvanced(start, end).subscribe((res) => {
      this.prepareCharts(res.daily_counts);
    });
  }
  private subscribeToWebSocket(): void {
    this.wsService.getBufferedStream().subscribe(batch => {
      this.updateData(batch);
    });
  }

  private updateData(batch: any[]): void {
    this.data = [...this.data, ...batch];
    // Tu peux connecter ceci à un virtual scroll si nécessaire
  }
}
